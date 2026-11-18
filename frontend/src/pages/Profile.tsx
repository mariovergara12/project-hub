import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { supabase } from '../lib/supabase';
import { useAuth } from '../auth-context';


export function Profile() {
    const { session } = useAuth();
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();
    
    return (
        // <div>
        //     <header className="pageTitle">
        //         <h1>
        //             My Profile
        //         </h1>
        //         <div className="profileButton">
        //             <button onClick={() => navigate('/main')}>
        //                 Back to Project Hub
        //             </button>
        //         </div>
        //     </header>

        //     <div className="basic-container">
        //         <h2>
        //             John Doe
        //         </h2>
        //         <h3>
        //             Computer Science - The University of Texas Rio Grande Valley
        //         </h3>
        //         <h4>
        //             Tag1 Tag2
        //         </h4>


        //         <div>
        //             <button onClick={() => navigate('/editprofile')}>
        //                 Edit profile
        //             </button>
        //         </div>

        //         <h2>
        //             About me
        //         </h2>
        //         <h4>
        //             I like programming 
        //         </h4>

        //         <h2>
        //             Skills
        //         </h2>
        //         <h3>
        //             Python React UI Design
        //         </h3>
        //         <h2>
        //             Interests
        //         </h2>
        //         <h3>
        //             Education Games Community
        //         </h3>

        //         <h2>
        //             Learning Goals
        //         </h2>
        //         <h3>
        //             I want to practice collaborating on a project
        //         </h3>

        //         <h2>
        //             Availability 
        //         </h2>
        //         <h3>
        //             6-8 Hours/Week
        //         </h3>
        //         <h4>
        //             Open to collboarting
        //         </h4>

        //         <h3>
        //             Background
        //         </h3>
        //         <h4>
        //             University
        //         </h4>
        //         <h4>
        //             UTRGV
        //         </h4>
        //         <h4>
        //             Major
        //         </h4>
        //         <h4>
        //             Computer Science
        //         </h4>
        //         <h4>
        //             Experience
        //         </h4>
        //         <h4>
        //             2 Years
        //         </h4>
        //     </div>

        // </div>
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

export default Profile;