import { createClient } from '@supabase/supabase-js';

// Public client settings. Passwords and server-side keys never belong here.
export const supabase = createClient(
    import.meta.env.VITE_SUPABASE_URL || 'https://wxycbijrtsofvhgtoxgs.supabase.co',
    import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || 'sb_publishable_EDLrI6w8HnSDSLkn281vog_6hp2oAur',
);
