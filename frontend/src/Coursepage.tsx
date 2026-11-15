import { useNavigate } from "react-router-dom";

export function ProjectHub() {
    const navigate = useNavigate();
    return (
        <div className="projecthub">
            <header>
                <h1>
                    Project Hub
                </h1>

                <button onClick={() => navigate('/profile')}>
                    Profile
                </button>
            </header>
        </div>
    )
}