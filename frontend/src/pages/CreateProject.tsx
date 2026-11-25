import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { supabase } from '../lib/supabase';
// import { getData } from "../api"; 
import { useAuth } from '../auth-context';


export function UserProject() {
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

            <div className="create-project-grid">
            <div></div>
            <div className="create-project-center">
                <div className="create-project-row-1">
                    <h1>
                        Create a Project
                    </h1>
                </div>
                <div className="create-project-row-2">
                    <div className="create-project-box">
                        <h2> Title </h2>
                        <div className="create-project-input">
                            <input></input>
                        </div>
                        <h2> Description </h2>
                        <div className="create-project-input"> 
                            <input></input>
                        </div>
                        <h2> Project Type </h2>
                        <div className="create-project-input">
                            <input></input>
                        </div>
                        <h2> Weekly Hours </h2>
                        <div className="create-project-input">
                            <input></input>
                        </div>
                        <h2> Minimum Experience Years </h2>
                        <div className="create-project-input">
                            <input></input>
                        </div>
                        <h2> Max Members </h2>
                        <div className="create-project-input">
                            <input></input>
                        </div>
                        <h2> Skills </h2>
                        <div className="create-project-input">
                            <input></input>
                        </div>
                        <div className="create-btn">
                            <button className="create-project-btn">
                                Submit
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div></div>
            </div>

            <>
                {message && <p role="status">{message}</p>}
                {error && <p role="alert">{error}</p>} 
            </>
        </>
    )
}

export default UserProject