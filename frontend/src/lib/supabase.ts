import { createClient } from '@supabase/supabase-js';
import { isRecovery, recordRecovery } from './auth-recovery';

// Public client settings. Passwords and server-side keys never belong here.
export const supabase = createClient(
    import.meta.env.VITE_SUPABASE_URL || 'https://wxycbijrtsofvhgtoxgs.supabase.co',
    import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || 'sb_publishable_EDLrI6w8HnSDSLkn281vog_6hp2oAur',
);

// Subscribe before React mounts so a recovery callback cannot be missed.
const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
    if (event === 'PASSWORD_RECOVERY' && session) recordRecovery(session.user.id);
    else if (!session || !isRecovery(session.user.id)) recordRecovery(null);
});

if (import.meta.hot) import.meta.hot.dispose(() => subscription.unsubscribe());
