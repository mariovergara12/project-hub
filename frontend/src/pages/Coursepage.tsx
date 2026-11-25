import { useNavigate } from "react-router-dom";
import { useEffect, useState } from 'react';
import { useAuth } from '../auth-context';
import { supabase } from "../lib/supabase";
import { getData } from "../api"; 
import '../App.css'

function Projects() {
    type project = {
        id: number;
        title: string;
        description: string;
    };

    const [projects, setProjects] = useState<project[]>([]);
    // const [pending, setPending] = useState(false);
    // const [message, setMessage] = useState('');
    // const [error, setError] = useState('');

    useEffect(() => {
        async function loadProjects() {
            try {
                const { data, error: sessionError } = await supabase.auth.getSession();
                if (sessionError) throw sessionError;
                if (!data.session) throw new Error('Please log in again');
            const sessionToken = data.session.access_token;
            const response = await getData('/projects?limit=100', sessionToken);

            console.log(response);
            setProjects(response.items);
            } catch (cause) {
                console.error(cause);
            }
        }
        loadProjects();
    }, []);    

    console.log(projects);
    return (
        <div className="projects-container">
            {projects.map((project) => (
                <div key={project.id} className="project-card">
                    <div>
                        <h2>
                            {project.title}
                        </h2>
                        <p>{project.description}</p>
                    </div>
                </div>
            ))}
        </div>
    )
}




export function ProjectHub() {
    const { session } = useAuth();
    // const [pending, setPending] = useState(false);
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
                            <li><a onClick={() => navigate("/projects")}> My Projects </a></li>
                            <li><a onClick={() => navigate("/profile")}> Profile </a></li>
                            <li><a onClick={() => signOut()}> Log out </a></li>
                        </ul>
                    </nav>
                </div>
            </header>

            <div className="main-grid-container">
                <div className="left">
                    <div className="createButton">
                        <button onClick={() => navigate("/createproject")}>
                            Create Project
                        </button>
                    </div>
                </div>


                <div className="center">
                    <h2>
                        {message && <p role="status">{message}</p>}
                        {error && <p role="alert">{error}</p>}                        
                    </h2>
                    <div>
                        <h1>
                            Central Project Manager
                        </h1>
                        <form>
                            {/* <input type="text" placeholder="Search Projects"></input> */}
                            <div className="search-input-container">
                                <input className="search-input" id="project-search" name="text" type="text" placeholder="Find Projects"/>
                                <div className="search-topline"></div>
                                <div className="search-underline"></div>
                            </div>
                        </form>
                    </div>
                    <div>
                        <Projects/>
                    </div>
                </div>

                
                <div className="right">
                    <div className="currProjectsButton">
                        <button onClick={() => console.log("CURRENT PROJECTS!")}>
                            Current Projects
                        </button>
                    </div>
                </div>

            </div>


        </>
    )
}
