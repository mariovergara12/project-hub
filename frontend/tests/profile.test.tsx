// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { Profile } from '../src/Profile';
import type { Me } from '../src/types';

const mocks = vi.hoisted(() => ({ patch: vi.fn(), resource: vi.fn(), reload: vi.fn() }));
vi.mock('../src/api', () => ({ api: { patch: mocks.patch } }));
vi.mock('../src/use-resource', () => ({ useResource: mocks.resource }));
vi.mock('../src/AccountAccess', () => ({ AccountAccess: () => null }));
vi.mock('../src/ProfileSelections', () => ({ ProfileSelections: () => null }));

const me: Me = { id: 'user-a', role: 'student', faculty_verified_at: null, profile: null, skills: [], interests: [] };
beforeEach(() => {
    vi.resetAllMocks();
    mocks.resource.mockReturnValue({ data: me, loading: false, reload: mocks.reload });
});
afterEach(cleanup);
const show = () => render(<MemoryRouter><Profile /></MemoryRouter>);
it('shows a loading state while the profile is being read', () => {
    mocks.resource.mockReturnValue({ loading: true });
    show();
    expect(screen.getByRole('status').textContent).toContain('Loading your profile');
});
it('offers profile creation without editable role or verification fields', () => {
    show();
    expect(screen.getByText('Complete your profile')).toBeTruthy();
    expect(screen.getByText('student')).toBeTruthy();
    expect(screen.queryByRole('textbox', { name: /role|verification/i })).toBeNull();
});
it('saves zero values, clears optional fields, and reloads server data', async () => {
    mocks.patch.mockResolvedValue({});
    show();
    const user = userEvent.setup();
    await user.type(screen.getByRole('textbox', { name: 'Display name' }), 'New student');
    await user.type(screen.getByRole('spinbutton', { name: 'Weekly availability (hours)' }), '0');
    await user.type(screen.getByRole('spinbutton', { name: 'Experience (years)' }), '0');
    await user.click(screen.getByRole('button', { name: 'Save profile' }));
    expect(mocks.patch).toHaveBeenCalledExactlyOnceWith('/me/profile', {
        display_name: 'New student', university: null, major: null, department: null,
        bio: null, availability_hours: 0, experience_years: 0, learning_goals: null,
    });
    expect(mocks.reload).toHaveBeenCalledTimes(1);
    expect(screen.getByText('Profile saved.')).toBeTruthy();
});
it('blocks repeat submissions while the save is pending', async () => {
    let finish!: (value: unknown) => void;
    mocks.patch.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    show();
    const user = userEvent.setup();
    await user.type(screen.getByRole('textbox', { name: 'Display name' }), 'Student');
    await user.click(screen.getByRole('button', { name: 'Save profile' }));
    const saving = screen.getByRole('button', { name: 'Saving…' });
    expect(saving.closest('fieldset')?.disabled).toBe(true);
    await user.click(saving);
    expect(mocks.patch).toHaveBeenCalledTimes(1);
    finish({});
    await waitFor(() => expect(mocks.reload).toHaveBeenCalledTimes(1));
});
it('keeps form values and shows a failed save instead of reporting success', async () => {
    mocks.patch.mockRejectedValue(new Error('Could not reach the service.'));
    show();
    const user = userEvent.setup();
    await user.type(screen.getByRole('textbox', { name: 'Display name' }), 'Unsaved student');
    await user.click(screen.getByRole('button', { name: 'Save profile' }));
    expect(screen.getByRole('alert').textContent).toContain('Could not reach');
    expect((screen.getByRole('textbox', { name: 'Display name' }) as HTMLInputElement).value).toBe('Unsaved student');
    expect(mocks.reload).not.toHaveBeenCalled();
    expect(screen.queryByText('Profile saved.')).toBeNull();
});
it('offers a retry when the initial profile request fails', async () => {
    mocks.resource.mockReturnValue({ error: new Error('Service unavailable'), loading: false, reload: mocks.reload });
    show();
    expect(screen.getByRole('alert').textContent).toContain('Service unavailable');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry profile' }));
    expect(mocks.reload).toHaveBeenCalledTimes(1);
});
