import { createContext, useContext } from 'react';
import type { Session } from '@supabase/supabase-js';

export const AuthContext = createContext<{ session: Session | null; loading: boolean; recovery: boolean; finishRecovery: () => void }>({
    session: null,
    loading: true,
    recovery: false,
    finishRecovery: () => {},
});

export function useAuth() {
    return useContext(AuthContext);
}
