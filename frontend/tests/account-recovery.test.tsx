// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AccountWelcome, AuthCallback, ForgotPassword, ResetPassword } from '../src/AccountRecovery';
import { AuthProvider } from '../src/AuthProvider';
import { Login } from '../src/Login';
import { RequireAuth } from '../src/RequireAuth';
import { isRecovery, recordRecovery } from '../src/lib/auth-recovery';

const mocks = vi.hoisted(() => ({ reset: vi.fn(), update: vi.fn(), signup: vi.fn(), signin: vi.fn(), resource: vi.fn(), auth: vi.fn(), changed: vi.fn(), finish: vi.fn() }));
vi.mock('../src/lib/supabase', () => ({ supabase: { auth: { resetPasswordForEmail: mocks.reset, updateUser: mocks.update, signUp: mocks.signup, signInWithPassword: mocks.signin, onAuthStateChange: mocks.changed } } }));
vi.mock('../src/use-resource', () => ({ useResource: mocks.resource }));
vi.mock('../src/auth-context', async importOriginal => ({ ...await importOriginal<object>(), useAuth: mocks.auth }));
function show(element: React.ReactNode, path = '/') {
    return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/" element={element} /><Route path="/welcome" element={<h1>Welcome route</h1>} /><Route path="/reset-password" element={<h1>Reset route</h1>} /><Route path="/profile" element={<h1>Profile setup route</h1>} /><Route path="/main" element={<h1>Explore route</h1>} /></Routes></MemoryRouter>);
}
beforeEach(() => {
    vi.resetAllMocks(); recordRecovery(null);
    mocks.auth.mockReturnValue({ session: null, loading: false, recovery: false, finishRecovery: mocks.finish });
    mocks.reset.mockResolvedValue({ error: null }); mocks.update.mockResolvedValue({ error: null });
});
afterEach(cleanup);
it('sends a trimmed email to Supabase with the local reset route and generic feedback', async () => {
    show(<ForgotPassword />); const user = userEvent.setup();
    await user.type(screen.getByLabelText('Email'), 'student@example.com');
    await user.click(screen.getByRole('button', { name: 'Send reset link' }));
    expect(mocks.reset).toHaveBeenCalledExactlyOnceWith('student@example.com', { redirectTo: `${window.location.origin}/reset-password` });
    expect(screen.getByRole('status').textContent).toContain('If an account exists');
});
it('prevents duplicate requests and keeps the email after a send error', async () => {
    let finish!: (value: unknown) => void;
    mocks.reset.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    show(<ForgotPassword />); const user = userEvent.setup();
    await user.type(screen.getByLabelText('Email'), 'student@example.com');
    await user.click(screen.getByRole('button', { name: 'Send reset link' }));
    fireEvent.submit(screen.getByLabelText('Email').closest('form')!);
    expect(mocks.reset).toHaveBeenCalledTimes(1);
    await act(async () => finish({ error: new Error('Please wait before requesting again.') }));
    expect(screen.getByRole('alert').textContent).toContain('Please wait');
    expect((screen.getByLabelText('Email') as HTMLInputElement).value).toBe('student@example.com');
});
it('does not let an ordinary session reset a password through a missing recovery link', () => {
    mocks.auth.mockReturnValue({ session: { user: { id: 'user' } }, loading: false, recovery: false });
    show(<ResetPassword />);
    expect(screen.getByRole('alert').textContent).toContain('expired');
    expect(screen.queryByLabelText('New password')).toBeNull();
    expect(mocks.update).not.toHaveBeenCalled();
});
it('validates confirmation and saves only the password through Supabase', async () => {
    mocks.auth.mockReturnValue({ session: { user: { id: 'user' } }, loading: false, recovery: true, finishRecovery: mocks.finish });
    show(<ResetPassword />); const user = userEvent.setup();
    await user.type(screen.getByLabelText('New password', { exact: true }), 'long-new-password');
    await user.type(screen.getByLabelText('Confirm new password'), 'different-password');
    await user.click(screen.getByRole('button', { name: 'Save new password' }));
    expect(mocks.update).not.toHaveBeenCalled();
    expect(screen.getByRole('alert').textContent).toContain('do not match');
    await user.clear(screen.getByLabelText('Confirm new password'));
    await user.type(screen.getByLabelText('Confirm new password'), 'long-new-password');
    await user.click(screen.getByRole('button', { name: 'Save new password' }));
    expect(mocks.update).toHaveBeenCalledExactlyOnceWith({ password: 'long-new-password' });
    expect(mocks.finish).toHaveBeenCalledOnce();
    expect(screen.getByRole('heading', { name: 'Password updated' })).toBeTruthy();
    expect(screen.queryByLabelText('New password')).toBeNull();
});
it('keeps reset errors retryable and does not clear recovery before success', async () => {
    mocks.auth.mockReturnValue({ session: { user: { id: 'user' } }, loading: false, recovery: true, finishRecovery: mocks.finish });
    mocks.update.mockResolvedValue({ error: new Error('Choose a different password.') });
    show(<ResetPassword />); const user = userEvent.setup();
    await user.type(screen.getByLabelText('New password', { exact: true }), 'new-password');
    await user.type(screen.getByLabelText('Confirm new password'), 'new-password');
    await user.click(screen.getByRole('button', { name: 'Save new password' }));
    expect(screen.getByRole('alert').textContent).toContain('Choose a different');
    expect(mocks.finish).not.toHaveBeenCalled();
});
it('shows a useful callback failure without a confirmed session', () => {
    show(<AuthCallback />);
    expect(screen.getByRole('alert').textContent).toContain('expired');
    expect(screen.getByRole('link', { name: 'Return to log in or sign up' })).toBeTruthy();
});
it('routes a confirmed signup to onboarding, and an existing profile to discovery', () => {
    mocks.resource.mockReturnValue({ data: { profile: null }, loading: false });
    const view = show(<AccountWelcome />);
    expect(screen.getByRole('heading', { name: 'Profile setup route' })).toBeTruthy();
    view.unmount(); mocks.resource.mockReturnValue({ data: { profile: { display_name: 'Student' } }, loading: false });
    show(<AccountWelcome />);
    expect(screen.getByRole('heading', { name: 'Explore route' })).toBeTruthy();
});
it('routes recovery sessions away from protected pages', () => {
    mocks.auth.mockReturnValue({ session: { user: { id: 'user' } }, loading: false, recovery: true });
    show(<RequireAuth />);
    expect(screen.getByRole('heading', { name: 'Reset route' })).toBeTruthy();
});
it('validates new signup passwords and provides an explicit confirmation callback', async () => {
    mocks.signup.mockResolvedValue({ data: { session: null }, error: null });
    show(<Login />); const user = userEvent.setup();
    await user.type(screen.getByLabelText('Email'), 'student@example.com');
    await user.type(screen.getByLabelText('Password'), 'short');
    await user.click(screen.getByRole('button', { name: 'Sign Up' }));
    expect(mocks.signup).not.toHaveBeenCalled();
    expect(screen.getByRole('alert').textContent).toContain('8 characters');
    await user.clear(screen.getByLabelText('Password'));
    await user.type(screen.getByLabelText('Password'), 'long-password');
    await user.click(screen.getByRole('button', { name: 'Sign Up' }));
    expect(mocks.signup).toHaveBeenCalledExactlyOnceWith({ email: 'student@example.com', password: 'long-password', options: { emailRedirectTo: `${window.location.origin}/auth/callback` } });
    expect(screen.getByRole('status').textContent).toContain('Check your email');
});
it('persists recovery intent across refresh events and clears it on account switch', async () => {
    let notify!: (event: string, session: unknown) => void;
    mocks.changed.mockImplementation(callback => { notify = callback; return { data: { subscription: { unsubscribe: vi.fn() } } }; });
    // Read the actual provider context; other tests mock only the hook consumers.
    const { AuthContext } = await import('../src/auth-context');
    const { useContext } = await import('react');
    function Status() { const auth = useContext(AuthContext); return <span>{auth.recovery ? 'Recovery active' : 'Ordinary session'}</span>; }
    render(<AuthProvider><Status /></AuthProvider>);
    act(() => notify('PASSWORD_RECOVERY', { user: { id: 'a' } }));
    expect(screen.getByText('Recovery active')).toBeTruthy();
    expect(isRecovery('a')).toBe(true);
    act(() => notify('TOKEN_REFRESHED', { user: { id: 'a' } }));
    expect(screen.getByText('Recovery active')).toBeTruthy();
    act(() => notify('SIGNED_IN', { user: { id: 'b' } }));
    expect(screen.getByText('Ordinary session')).toBeTruthy();
    expect(isRecovery('a')).toBe(false);
    expect(sessionStorage.getItem('project-hub-recovery-user')).toBeNull();
});
it('ignores a late password-save result after switching accounts', async () => {
    let finish!: (value: unknown) => void;
    mocks.update.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    mocks.auth.mockReturnValue({ session: { user: { id: 'a' } }, loading: false, recovery: true, finishRecovery: mocks.finish });
    const view = render(<MemoryRouter><ResetPassword /></MemoryRouter>); const user = userEvent.setup();
    await user.type(screen.getByLabelText('New password', { exact: true }), 'new-password');
    await user.type(screen.getByLabelText('Confirm new password'), 'new-password');
    await user.click(screen.getByRole('button', { name: 'Save new password' }));
    mocks.auth.mockReturnValue({ session: { user: { id: 'b' } }, loading: false, recovery: false, finishRecovery: mocks.finish });
    view.rerender(<MemoryRouter><ResetPassword /></MemoryRouter>);
    await act(async () => finish({ error: null }));
    expect(screen.queryByRole('heading', { name: 'Password updated' })).toBeNull();
    expect(mocks.finish).not.toHaveBeenCalled();
});
