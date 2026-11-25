import { useNavigate } from 'react-router-dom';
import { NavBar } from '../Components';

export function EditProfile() {
    const navigate = useNavigate();

    return (
        <>
            <NavBar></NavBar>
            <div className="pageTitle basic-container">
                <h1>
                    Edit Profile
                </h1>
                <button onClick={() => navigate("/profile")}>
                    Submit Changes
                </button>
            </div>

        </>
    )
}

export default EditProfile