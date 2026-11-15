import { useNavigate } from "react-router-dom";
import './App.css'

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
            </div>
        </>
    )
}