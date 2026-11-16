import { createContext, useContext } from 'react';
import type { Session } from '@supabase/supabase-js';

export const AuthContext = createContext<{ session: Session | null; loading: boolean }>({
    session: null,
    loading: true,
});

export function useAuth() {
    return useContext(AuthContext);
}
