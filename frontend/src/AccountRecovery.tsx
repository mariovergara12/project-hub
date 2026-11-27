import { useEffect, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from './auth-context';
import { supabase } from './lib/supabase';
import { authLinkError } from './lib/auth-recovery';
import { Brand, PageLoading } from './ui';
import { useResource } from './use-resource';
import type { Me } from './types';

function AccountPage({ title, children }: { title: string; children: ReactNode }) {
    return <div className="account-page"><header><Brand linked={false} /></header><main className="login-card"><h1>{title}</h1>{children}</main><footer><Link to="/">Back to log in</Link></footer></div>;
}

export function ForgotPassword() {
    const active = useRef(false);
    const [pending, setPending] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState('');
    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (active.current) return;
        const email = String(new FormData(event.currentTarget).get('email') || '').trim();
        active.current = true;
        setPending(true); setError('');
        try {
            const result = await supabase.auth.resetPasswordForEmail(email, { redirectTo: `${window.location.origin}/reset-password` });
            if (result.error) throw result.error;
            setSent(true);
        } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not send the reset link. Please try again.'); }
        finally { active.current = false; setPending(false); }
    }
    return <AccountPage title="Reset your password">
        {sent ? <div role="status"><h2>Check your email</h2><p>If an account exists for that address, you’ll receive a password reset link. Open it to choose a new password.</p><p>Check your spam folder too. If the link expires, request a new one.</p><button onClick={() => setSent(false)}>Request another link</button></div> : <>
            <p>Enter your account email and we’ll send a link to choose a new password.</p>
            <form onSubmit={submit} aria-busy={pending}><fieldset className="profile-fields" disabled={pending}><legend>Account email</legend><label>Email<input name="email" type="email" autoComplete="email" required /></label><button type="submit" className="button-primary">{pending ? 'Sending…' : 'Send reset link'}</button></fieldset></form>
        </>}{error && <p role="alert">{error}</p>}
    </AccountPage>;
}

export function ResetPassword() {
    const { session } = useAuth();
    return <ResetPasswordPage key={session?.user.id || 'anonymous'} />;
}

function ResetPasswordPage() {
    const { session, loading, recovery, finishRecovery } = useAuth();
    const active = useRef(false);
    const mounted = useRef(true);
    useEffect(() => {
        mounted.current = true;
        return () => { mounted.current = false; };
    }, []);
    const [pending, setPending] = useState(false);
    const [saved, setSaved] = useState(false);
    const [error, setError] = useState('');
    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (active.current || !session || !recovery || authLinkError) return;
        const values = new FormData(event.currentTarget);
        const password = String(values.get('password') || '');
        if (password.length < 8) { setError('Use at least 8 characters.'); return; }
        if (password !== values.get('confirmation')) { setError('The passwords do not match.'); return; }
        active.current = true; setPending(true); setError('');
        try {
            const result = await supabase.auth.updateUser({ password });
            if (result.error) throw result.error;
            if (mounted.current) { setSaved(true); finishRecovery(); }
        } catch (cause) { if (mounted.current) setError(cause instanceof Error ? cause.message : 'Could not save your password. Please try again.'); }
        finally { active.current = false; if (mounted.current) setPending(false); }
    }
    if (loading) return <AccountPage title="Checking your reset link"><PageLoading /></AccountPage>;
    return <AccountPage title={saved ? 'Password updated' : 'Choose a new password'}>
        {saved ? <div role="status"><p>Your new password is saved. You can now continue to your workspace.</p><Link className="button button-primary" to="/welcome">Continue to Project Hub</Link></div>
            : !session || !recovery || authLinkError ? <><p role="alert">This reset link is missing, expired, or already used.</p><Link className="button" to="/forgot-password">Request a new reset link</Link></>
            : <><p>Use a password with at least 8 characters that you don’t use elsewhere.</p><form onSubmit={submit} aria-busy={pending}><fieldset className="profile-fields" disabled={pending}><legend>New password</legend>
                <label>New password<input name="password" type="password" autoComplete="new-password" minLength={8} required /></label>
                <label>Confirm new password<input name="confirmation" type="password" autoComplete="new-password" minLength={8} required /></label>
                <button type="submit" className="button-primary">{pending ? 'Saving…' : 'Save new password'}</button>
            </fieldset></form></>}
        {error && <p role="alert">{error}</p>}
    </AccountPage>;
}

export function AuthCallback() {
    const { session, loading, recovery } = useAuth();
    if (loading) return <AccountPage title="Confirming your account"><PageLoading /></AccountPage>;
    if (authLinkError || !session) return <AccountPage title="This link is no longer valid"><p role="alert">Your confirmation link may have expired or already been used.</p><p>Try logging in if you already confirmed your email, or sign up again to request a fresh confirmation.</p><Link className="button" to="/">Return to log in or sign up</Link></AccountPage>;
    return <Navigate to={recovery ? '/reset-password' : '/welcome'} replace />;
}

export function AccountWelcome() {
    const me = useResource<Me>('/me');
    if (me.loading) return <main className="app-page"><PageLoading>Opening your workspace…</PageLoading></main>;
    if (me.error) return <main className="app-page"><p role="alert">{me.error.message} <button onClick={me.reload}>Retry account</button></p></main>;
    return <Navigate to={me.data?.profile ? '/main' : '/profile?welcome=1'} replace />;
}
