type Session = { access_token: string; user: { id: string } };
type AuthResult = { data: { session: Session | null }; error: { message: string } | null };
type Auth = {
    getSession(): Promise<AuthResult>;
    refreshSession(): Promise<AuthResult>;
    signOut(options: { scope: 'local' }): Promise<{ error: { message: string } | null }>;
};

export class ApiError extends Error {
    readonly status: number;
    constructor(status: number, message: string) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
    }
}

async function errorMessage(response: Response): Promise<string> {
    const fallback = response.status >= 500
        ? 'The service is temporarily unavailable. Please try again.'
        : `Request failed (${response.status}). Please try again.`;
    try {
        const { detail } = await response.json();
        if (typeof detail === 'string') return detail;
        if (Array.isArray(detail)) {
            return detail.map(item => {
                const field = Array.isArray(item.loc) ? item.loc.slice(1).join('.') : '';
                return `${field ? field + ': ' : ''}${item.msg || 'Invalid value'}`;
            }).join('; ');
        }
    } catch { /* Non-JSON server errors still get a useful message. */ }
    return fallback;
}

export function createApiClient({ baseUrl, auth, fetcher = fetch }: {
    baseUrl: string; auth: Auth; fetcher?: typeof fetch;
}) {
    let refresh: { token: string; promise: Promise<AuthResult> } | undefined;
    async function requireSession(userId?: string) {
        const result = await auth.getSession();
        if (result.error || !result.data.session) {
            throw new ApiError(401, 'Your session has ended. Please log in again.');
        }
        if (userId && result.data.session.user.id !== userId) {
            throw new ApiError(401, 'The signed-in account changed. Please reload this page.');
        }
        return result.data.session;
    }
    async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
        if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Use an API path.');
        const initial = await requireSession();
        const userId = initial.user.id;
        async function send(token: string) {
            const headers = new Headers(options.headers);
            headers.set('Authorization', `Bearer ${token}`);
            if (options.body) headers.set('Content-Type', 'application/json');
            try {
                return await fetcher(baseUrl.replace(/\/$/, '') + path, {
                    ...options, headers, credentials: 'omit',
                });
            } catch (error) {
                if (options.signal?.aborted) throw error;
                throw new ApiError(0, 'Could not reach the service. Check your connection and try again.');
            }
        }
        let response = await send(initial.access_token);
        let current = await requireSession(userId);
        if (response.status === 401) {
            if (current.access_token === initial.access_token) {
                // Concurrent requests share a refresh; each request retries at most once.
                if (!refresh || refresh.token !== current.access_token) {
                    refresh = { token: current.access_token, promise: auth.refreshSession() };
                }
                const activeRefresh = refresh;
                let result: AuthResult;
                try { result = await activeRefresh.promise; }
                catch { result = { data: { session: null }, error: { message: 'Refresh failed' } }; }
                finally { if (refresh === activeRefresh) refresh = undefined; }
                await requireSession(userId);
                if (result.error || !result.data.session) {
                    await auth.signOut({ scope: 'local' });
                    throw new ApiError(401, 'Your session has ended. Please log in again.');
                }
                current = result.data.session;
                if (current.user.id !== userId) throw new ApiError(401, 'The signed-in account changed.');
            }
            response = await send(current.access_token);
            await requireSession(userId);
            if (response.status === 401) {
                await auth.signOut({ scope: 'local' });
                throw new ApiError(401, 'Your session has ended. Please log in again.');
            }
        }
        if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
        return response.json() as Promise<T>;
    }
    return {
        get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
        patch: <T>(path: string, body: unknown, signal?: AbortSignal) => request<T>(path, {
            method: 'PATCH', body: JSON.stringify(body), signal,
        }),
    };
}
