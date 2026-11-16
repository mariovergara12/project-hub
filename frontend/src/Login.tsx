import { useState } from 'react';
import type { FormEvent } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from './auth-context';
import { supabase } from './lib/supabase';

export function Login() {
    const { session, loading } = useAuth();
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
                const { data, error: signUpError } = await supabase.auth.signUp({ email, password });
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

    if (loading) return <p role="status">Loading your session…</p>;
    if (session) return <Navigate to="/main" replace />;

    return (
        <div className="login-page">
            <header className="pageTitle"><h1>Project Hub</h1></header>
            <main className="basic-container login-container">
                <div className="login-card">
                    <h2>Welcome to Project Hub</h2>
                    <p>Log in with your Project Hub account.</p>
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
                </div>
            </main>
        </div>
    );
}

export default Login;
