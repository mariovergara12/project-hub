import { useNavigate } from 'react-router-dom';

export function EditProfile() {
    const navigate = useNavigate();

    return (
        <>
            <div className="pageTitle">
                <h1 className="basic-container">
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