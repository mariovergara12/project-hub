import { describe, expect, it, vi } from 'vitest';
import { createApiClient } from '../src/lib/api-client';

type Session = { access_token: string; user: { id: string } };
function setup() {
    let session: Session | null = { access_token: 'old-token', user: { id: 'user-a' } };
    const auth = {
        getSession: vi.fn(async () => ({ data: { session }, error: null })),
        refreshSession: vi.fn(async (): Promise<{ data: { session: Session | null }; error: { message: string } | null }> => {
            session = { access_token: 'new-token', user: { id: 'user-a' } };
            return { data: { session }, error: null };
        }),
        signOut: vi.fn(async () => { session = null; return { error: null }; }),
    };
    const fetcher = vi.fn<typeof fetch>();
    const api = createApiClient({ baseUrl: 'https://api.example/', auth, fetcher });
    return { auth, fetcher, api, setSession: (value: Session | null) => { session = value; } };
}
const json = (status: number, body: unknown = {}) => new Response(JSON.stringify(body), {
    status, headers: { 'Content-Type': 'application/json' },
});

describe('authenticated API requests', () => {
    it('attaches the current token and serializes a profile update including zero/null', async () => {
        const { api, fetcher } = setup();
        fetcher.mockResolvedValue(json(200, { bio: null, availability_hours: 0 }));
        await expect(api.patch('/me/profile', { bio: null, availability_hours: 0 })).resolves.toEqual({ bio: null, availability_hours: 0 });
        const [url, init] = fetcher.mock.calls[0];
        expect(url).toBe('https://api.example/me/profile');
        expect(init?.method).toBe('PATCH');
        expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer old-token');
        expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json');
        expect(init?.credentials).toBe('omit');
    });
    it('does not send requests without a session', async () => {
        const { api, fetcher, setSession } = setup();
        setSession(null);
        await expect(api.get('/me')).rejects.toMatchObject({ status: 401 });
        expect(fetcher).not.toHaveBeenCalled();
    });
    it('refreshes once and retries a rejected request using the new token', async () => {
        const { api, fetcher, auth } = setup();
        fetcher.mockResolvedValueOnce(json(401)).mockResolvedValueOnce(json(200, { id: 'user-a' }));
        await expect(api.get('/me')).resolves.toEqual({ id: 'user-a' });
        expect(auth.refreshSession).toHaveBeenCalledTimes(1);
        expect(fetcher).toHaveBeenCalledTimes(2);
        expect(new Headers(fetcher.mock.calls[1][1]?.headers).get('Authorization')).toBe('Bearer new-token');
    });
    it('signs out after a failed refresh without retrying the request', async () => {
        const { api, fetcher, auth } = setup();
        fetcher.mockResolvedValue(json(401));
        auth.refreshSession.mockResolvedValue({ data: { session: null }, error: { message: 'Expired refresh token' } });
        await expect(api.get('/me')).rejects.toMatchObject({ status: 401 });
        expect(fetcher).toHaveBeenCalledTimes(1);
        expect(auth.signOut).toHaveBeenCalledExactlyOnceWith({ scope: 'local' });
    });
    it('stops after a second 401 instead of looping', async () => {
        const { api, fetcher, auth } = setup();
        fetcher.mockImplementation(async () => json(401));
        await expect(api.get('/projects')).rejects.toMatchObject({ status: 401 });
        expect(fetcher).toHaveBeenCalledTimes(2);
        expect(auth.refreshSession).toHaveBeenCalledTimes(1);
        expect(auth.signOut).toHaveBeenCalledTimes(1);
    });
    it('shares refresh across concurrent unauthorized requests', async () => {
        const { api, fetcher, auth, setSession } = setup();
        let finish!: () => void;
        const gate = new Promise<void>(resolve => { finish = resolve; });
        auth.refreshSession.mockImplementation(async () => {
            await gate;
            const session = { access_token: 'new-token', user: { id: 'user-a' } };
            setSession(session);
            return { data: { session }, error: null };
        });
        fetcher.mockImplementation(async (_url, init) => new Headers(init?.headers).get('Authorization') === 'Bearer old-token'
            ? json(401) : json(200, { ok: true }));
        const requests = Promise.all([api.get('/me'), api.get('/projects'), api.get('/skills')]);
        await vi.waitFor(() => expect(auth.refreshSession).toHaveBeenCalledTimes(1));
        finish();
        await expect(requests).resolves.toHaveLength(3);
        expect(auth.refreshSession).toHaveBeenCalledTimes(1);
        expect(fetcher).toHaveBeenCalledTimes(6);
    });
    it('uses a token already refreshed by another request without refreshing again', async () => {
        const { api, fetcher, auth, setSession } = setup();
        fetcher.mockImplementationOnce(async () => {
            setSession({ access_token: 'new-token', user: { id: 'user-a' } });
            return json(401);
        }).mockResolvedValueOnce(json(200));
        await api.get('/me');
        expect(auth.refreshSession).not.toHaveBeenCalled();
        expect(fetcher).toHaveBeenCalledTimes(2);
    });
    it('does not sign out or refresh on provider unavailability', async () => {
        const { api, fetcher, auth } = setup();
        fetcher.mockResolvedValue(json(503, { detail: 'Identity provider is unavailable' }));
        await expect(api.get('/me')).rejects.toMatchObject({ status: 503, message: 'Identity provider is unavailable' });
        expect(auth.refreshSession).not.toHaveBeenCalled();
        expect(auth.signOut).not.toHaveBeenCalled();
    });
    it.each([
        [422, { detail: 'display_name is required to create a profile' }, 'display_name is required to create a profile'],
        [422, { detail: [{ loc: ['body', 'availability_hours'], msg: 'Must be at most 168', input: 'private input' }] }, 'availability_hours: Must be at most 168'],
        [404, { detail: 'Project not found' }, 'Project not found'],
    ])('displays API error details without exposing input (%s)', async (status, body, message) => {
        const { api, fetcher } = setup();
        fetcher.mockResolvedValue(json(status, body));
        await expect(api.get('/me')).rejects.toMatchObject({ status, message });
    });
    it('handles a non-JSON server error', async () => {
        const { api, fetcher } = setup();
        fetcher.mockResolvedValue(new Response('<html>Bad Gateway</html>', { status: 502 }));
        await expect(api.get('/me')).rejects.toMatchObject({ status: 502, message: 'The service is temporarily unavailable. Please try again.' });
    });
    it('drops a previous account response without signing out the new account', async () => {
        const { api, fetcher, auth, setSession } = setup();
        fetcher.mockImplementation(async () => {
            setSession({ access_token: 'other-token', user: { id: 'user-b' } });
            return json(200, { private: 'user-a data' });
        });
        await expect(api.get('/me')).rejects.toMatchObject({ status: 401 });
        expect(auth.signOut).not.toHaveBeenCalled();
    });
    it('never replays a request after the account changes during refresh', async () => {
        const { api, fetcher, auth, setSession } = setup();
        fetcher.mockResolvedValue(json(401));
        auth.refreshSession.mockImplementation(async () => {
            const session = { access_token: 'other-token', user: { id: 'user-b' } };
            setSession(session);
            return { data: { session }, error: null };
        });
        await expect(api.get('/me')).rejects.toMatchObject({ status: 401 });
        expect(fetcher).toHaveBeenCalledTimes(1);
        expect(auth.signOut).not.toHaveBeenCalled();
    });
    it('shows network failures without an authentication retry', async () => {
        const { api, fetcher, auth } = setup();
        fetcher.mockRejectedValue(new TypeError('Failed to fetch'));
        await expect(api.get('/projects')).rejects.toMatchObject({ status: 0 });
        expect(auth.refreshSession).not.toHaveBeenCalled();
    });
    it('passes through request cancellation', async () => {
        const { api, fetcher } = setup();
        const controller = new AbortController();
        controller.abort();
        fetcher.mockRejectedValue(new DOMException('Aborted', 'AbortError'));
        await expect(api.get('/projects', controller.signal)).rejects.toMatchObject({ name: 'AbortError' });
    });
    it('rejects cross-origin URLs before sending credentials', async () => {
        const { api, fetcher } = setup();
        await expect(api.get('//unrelated.example/me')).rejects.toThrow('Use an API path');
        expect(fetcher).not.toHaveBeenCalled();
    });
});
