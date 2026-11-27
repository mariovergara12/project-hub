import { useState } from 'react';
import { useAuth } from './auth-context';
import { supabase } from './lib/supabase';
import { Icon } from './ui';

export function AccountAccess() {
    const { session } = useAuth();
    const [pending, setPending] = useState(false);
    const [error, setError] = useState('');
    async function signOut() {
        if (pending) return;
        setPending(true);
        setError('');
        try {
            const result = await supabase.auth.signOut({ scope: 'local' });
            if (result.error) throw result.error;
        } catch {
            setError('Could not log out. Please try again.');
        } finally { setPending(false); }
    }
    return <section className="account-access" aria-label="Your account">
        <p><span className="account-caption">Signed in as </span><strong>{session?.user.email}</strong></p>
        <button className="button-quiet" aria-label={pending ? 'Logging out…' : 'Log Out'} onClick={signOut} disabled={pending}><Icon name="logout" /><span className="logout-label">{pending ? 'Logging out…' : 'Log Out'}</span></button>
        {error && <p role="alert">{error}</p>}
    </section>;
}
