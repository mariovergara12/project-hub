import { NavBar } from '../Components';
import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { getData } from '../api';
import { useNavigate } from 'react-router-dom';


export function Profile() {
    const navigate = useNavigate();
    type profile = {
        display_name: string;
        university: string;
        major: string;
        department: string; 
        bio: string; 
        availablity_hours: number;
        learning_goals: string;
        experience_years: number;
    }

    const [profile, setProfile] = useState<profile[]>([]);

    useEffect(() => {
        async function loadProfile() {
            try {
                const { data, error: sessionError } = await supabase.auth.getSession();
                if (sessionError) throw sessionError;
                if (!data.session) throw new Error('Please log in again');
                const sessionToken = data.session.access_token;
                console.log(sessionToken)
                const response = await getData('/me', sessionToken);
                console.log(response);
                setProfile(response);
            } catch (cause) {
                console.error(cause);
            }
        }
        loadProfile();
    }, []);


    console.log(profile);
    return (
        <>
            <NavBar/>
            <div className="profile-grid-container">
                <div/> 
                <div className="profile-center">
                    <div className="profile-row-1">
                        <h1>
                            My Profile
                        </h1>
                        {/* <h2>
                            A little about myself
                        </h2> */}
                        <div className="profile-picture-info-box">
                            <div className="profile-picture">
                                <img src= "/hey.jpg" alt="Profile"/>  
                            </div>

                            <div className="profile-info">
                                <div className="profile-info-row-1">
                                    <div className="profilename">
                                        John Doe
                                    </div>
                                    <div className="profile-desc">
                                        Computer Science - The University of Texas Rio Grande Valley
                                    </div>
                                    <div className="skills-tag"> Student </div>
                                </div>
                            </div>

                            <div>
                                <button onClick={() => navigate('/editprofile')}>
                                    Edit Profile
                                </button>
                            </div>
                        </div>
                    </div>
                    <div className="profile-row-2">
                        <div className="profile-info-section">
                            <div className="profile-info-box">
                                <h2>
                                    About me
                                </h2>
                                <h3>
                                    I enjoy building websites and working with others in teams.
                                </h3>
                                <h2>
                                    Skills
                                </h2>
                                <div className="skills-container">
                                    <div className="skills-tag"> Wizardry </div>
                                    <div className="skills-tag"> Python </div>
                                    <div className="skills-tag"> C++ </div>
                                    <div className="skills-tag"> C# </div>
                                </div>
                                <h2>
                                    Interests
                                </h2>
                                <div className="skills-container">
                                    <div className="skills-tag"> Pickelball </div>
                                    <div className="skills-tag"> Football (American) </div>
                                    <div className="skills-tag"> Football (European) </div>
                                </div>
                                <h2>
                                    Learning Goals
                                </h2>
                                <h3>
                                    I want to practice collaborating on a project
                                </h3>
                            </div>
                            <div className= "profile-info-section-2">
                                <div className="profile-info-box"> 
                                    <h2>
                                        Availability
                                    </h2>
                                    <p className="availability-times">
                                        6-8 hours / week
                                    </p>
                                </div>
                                <div className="profile-info-box">
                                    <h2>
                                        Background
                                    </h2>
                                    <h4>
                                        University
                                    </h4>
                                    <h4>
                                        UTRGV
                                    </h4>
                                    <h4>
                                        Major
                                    </h4>
                                    <h4>
                                        Computer Science
                                    </h4>
                                    <h4>
                                        Experience
                                    </h4>
                                    <h4>
                                        2 years
                                    </h4>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div/>
            </div>
        </>
    )
}

export default Profile;