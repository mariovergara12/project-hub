import { useState } from 'react';
import { useAuth } from './auth-context';
import { supabase } from './lib/supabase';

export function AccountAccess() {
    const { session } = useAuth();
    const [pending, setPending] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');

    async function copyToken() {
        setPending(true);
        setMessage('');
        setError('');
        try {
            const { data, error: sessionError } = await supabase.auth.getSession();
            if (sessionError) throw sessionError;
            if (!data.session) throw new Error('Please log in again to get an access token.');
            await navigator.clipboard.writeText(data.session.access_token);
            setMessage('Token copied. Paste it into Authorize in the API docs, without adding Bearer.');
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : 'Could not copy the token. Please try again.');
        } finally {
            setPending(false);
        }
    }

    async function signOut() {
        setPending(true);
        setMessage('');
        setError('');
        try {
            const { error: signOutError } = await supabase.auth.signOut({ scope: 'local' });
            if (signOutError) throw signOutError;
        } catch {
            setError('Could not log out. Please try again.');
        } finally {
            setPending(false);
        }
    }

    return (
        <section className="account-access" aria-label="Your account">
            <p>Signed in as <strong>{session?.user.email}</strong></p>
            <button onClick={signOut} disabled={pending}>Log Out</button>
            <details>
                <summary>API testing</summary>
                <p>Copy your current access token to try protected endpoints in the API docs.</p>
                <div className="auth-actions">
                    <button onClick={copyToken} disabled={pending}>Copy API token</button>
                    <a href="https://project-hub-api-ruby.vercel.app/docs" target="_blank" rel="noreferrer">Open API docs</a>
                </div>
            </details>
            {message && <p role="status">{message}</p>}
            {error && <p role="alert">{error}</p>}
        </section>
    );
}
