import { useNavigate } from "react-router-dom";
import './App.css'
import { AccountAccess } from './AccountAccess';
import { useEffect, useState } from 'react';
// import { useAuth } from './auth-context';
import { supabase } from "./lib/supabase";
import { getData } from "./api"; 



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
            const response = await getData('/projects?limit=3', sessionToken);

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
        <div className="basic-container">
            <div className="project-cards">
                {projects.map((project) => (
                    <div key={project.id} className="project-card">
                        <h1>
                        Project
                        </h1>
                        <h3>{project.title}</h3>
                        <h4>{project.description}</h4>
                    </div>
                ))}
            </div>
        </div>
    )
}

export function ProjectHub() {
    const navigate = useNavigate();
    return (
        <>
            <div className="projecthub">
                <header className="pageTitle">

                    <div className="profileButton">
                        <button onClick={() => navigate('/profile')}>
                            Profile
                        </button>
                    </div>

                    <div className="createButton">
                        <button onClick={() => console.log('Left function')}>
                            Create Project
                        </button>
                    </div>
                    
                    <h1>
                        Project Hub
                    </h1>

                    <div className="currProjectsButton">
                        <button onClick={() => console.log("Right function")}>
                            Current Projects
                        </button>
                    </div>

                </header>
                <AccountAccess />

                <form onSubmit={async(event) => {
                    event.preventDefault();
                    const formData = new FormData(event.currentTarget);
                    const searchInput = formData.get('searchbox');
                    console.log(searchInput);
                }}>
                <div className="search-container">
                    <input type="text" placeholder="Search Projects" name="searchbox"/>
                </div>
                </form>

                <Projects/>
            </div>
        </>
    )
}
