import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from './auth-context';
import { supabase } from './lib/supabase';
import { Brand, CollaborationArt, PageLoading } from './ui';

export function Login() {
    const { session, loading, recovery } = useAuth();
    const [pending, setPending] = useState(false);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (pending) return;
        const form = event.currentTarget;
        const formData = new FormData(form);
        const email = String(formData.get('email') || '').trim();
        const password = String(formData.get('password') || '');
        const action = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
        setPending(true);
        setError('');
        setMessage('');
        try {
            if (action?.value === 'signup') {
                if (password.length < 8) throw new Error('Use at least 8 characters for a new password.');
                const { data, error: signUpError } = await supabase.auth.signUp({ email, password, options: { emailRedirectTo: `${window.location.origin}/auth/callback` } });
                if (signUpError) throw signUpError;
                if (!data.session) {
                    setMessage('Check your email to confirm your account, then return here to log in.');
                    form.reset();
                }
            } else {
                const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
                if (signInError) throw signInError;
            }
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : 'Could not sign in. Please try again.');
        } finally {
            setPending(false);
        }
    }

    if (loading) return <main className="app-page"><PageLoading>Loading your session…</PageLoading></main>;
    if (session) return <Navigate to={recovery ? '/reset-password' : '/welcome'} replace />;

    return (
        <div className="login-page">
            <header className="login-header"><Brand linked={false} /><span>Student projects. Faculty research. Shared ambition.</span></header>
            <main className="login-layout">
                <section className="login-intro"><p className="eyebrow">A place for your next idea</p><h1>Bring your ideas.<br />Find your people.</h1><p>Connect with students and faculty across disciplines. Find a project to join, or build a team around your own.</p><CollaborationArt /></section>
                <div className="login-card">
                    <h2>Make something happen.</h2>
                    <p>Log in to your account or sign up to get started.</p>
                    <form onSubmit={submit} aria-busy={pending}>
                        <div className="form-group">
                            <label htmlFor="email">Email</label>
                            <input type="email" id="email" name="email" autoComplete="username"
                                placeholder="Enter your email" required disabled={pending} />
                        </div>
                        <div className="form-group">
                            <label htmlFor="password">Password</label>
                            <input type="password" id="password" name="password" autoComplete="current-password"
                                placeholder="Enter your password" required disabled={pending} />
                        </div>
                        {error && <p role="alert">{error}</p>}
                        {message && <p role="status">{message}</p>}
                        <div className="auth-actions">
                            <button type="submit" className="login-button" value="login" disabled={pending}>
                                {pending ? 'Please wait…' : 'Log In'}
                            </button>
                            <button type="submit" className="signup-button" value="signup" disabled={pending}>Sign Up</button>
                        </div>
                    </form>
                    <p><Link to="/forgot-password">Forgot your password?</Link></p>
                    <p className="auth-caption">Your profile, projects, and applications stay connected to your account.</p>
                </div>
            </main>
            <footer className="login-footer">Project Hub · Built for collaboration across campus.</footer>
        </div>
    );
}

export default Login;
