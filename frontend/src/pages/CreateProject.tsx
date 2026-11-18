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
            {/* <h1 className="basic-container">
                Create your project
            </h1>

            <form className="form-group">
                <div className="basic-container">
                    <input type="text" placeholder="Enter Project Title"></input>
                </div>
                <div className="basic-container">
                    <input type="text" placeholder="Enter Project Fields"></input>
                </div>
                <div className="basic-container">
                    <input type="text" placeholder="Enter Project Description"></input>
                </div>
                <div className="basic-container">
                    <button onClick={() => console.log("FUNCTION!")}>
                        Submit
                    </button>
                </div>
                <div className="basic-container"> 
                    <button onClick={() => navigate("/main")}>
                        Back to Main
                    </button>
                </div>
            </form> */}
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

export default UserProject