import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { supabase } from './lib/supabase';
import { useAuth } from './auth-context';


export function NavBar() {
    const { session } = useAuth();
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

        async function signOut() {
    // setPending(true);
        setMessage('');
        setError('');
        try {
            const { error: signOutError } = await supabase.auth.signOut({ scope: 'local' });
            if (signOutError) throw signOutError;
        } catch {
            setError('Could not log out. Please try again.');
        } finally {
            // setPending(false);
        }
    } 

    return (
        <>
            <header>
                <div className="container">
                    <div id="userProfile"> {session?.user.email} </div>
                    <nav>
                        <ul className="nav-links">
                            <li><a onClick={() => navigate("/main")}> Home</a></li>
                            <li><a onClick={() => navigate("/projects")}> My Projects </a></li>
                            <li><a onClick={() => navigate("/profile")}> Profile </a></li>
                            <li><a onClick={() => signOut()}> Log out </a></li>
                        </ul>
                    </nav>
                </div>
            </header>
            <>
                {message && <p role="status">{message}</p>}
                {error && <p role="alert">{error}</p>} 
            </>
        </>
    )
}
