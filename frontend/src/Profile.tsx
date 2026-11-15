import { useNavigate } from "react-router-dom";

export function Profile() {
    const navigate = useNavigate();
    
    return (
        <div>
            <header className="pageTitle">
                <h1>
                    Profile Mainpage & Settings
                </h1>
            </header>

            <div className="basic-container">
                <button onClick={() => navigate('/main')}>
                    Back to Project Hub
                </button>
            </div>


        </div>
    )
}

export default Profile;