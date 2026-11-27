import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import type { Session } from '@supabase/supabase-js';
import { AuthContext } from './auth-context';
import { supabase } from './lib/supabase';
import { isRecovery, recordRecovery } from './lib/auth-recovery';

export function AuthProvider({ children }: { children: ReactNode }) {
    const [session, setSession] = useState<Session | null>(null);
    const [loading, setLoading] = useState(true);
    const [recovery, setRecovery] = useState(false);

    useEffect(() => {
        const { data: { subscription } } = supabase.auth.onAuthStateChange((event, nextSession) => {
            if (event === 'PASSWORD_RECOVERY' && nextSession) recordRecovery(nextSession.user.id);
            else if (!nextSession || !isRecovery(nextSession.user.id)) recordRecovery(null);
            setSession(nextSession);
            setRecovery(isRecovery(nextSession?.user.id));
            setLoading(false);
        });
        return () => subscription.unsubscribe();
    }, []);

    return <AuthContext value={{ session, loading, recovery, finishRecovery: () => { recordRecovery(null); setRecovery(false); } }}>{children}</AuthContext>;
}
