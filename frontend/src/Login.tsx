import { useNavigate } from 'react-router-dom'; 


export function Login() {
const navigate = useNavigate();


    return (
        <div className="login-page">
            <header className="login-header">
                <h1>Project Hub</h1>

                <p>
                <a href="/signup">Sign Up</a>
                </p>
            </header>

            <main className="login-container">
                <div className="login-card">
                    <h2>Welcome Back</h2>
                    <p>Log in</p>

                    <form onSubmit={async(event) => {
                        event.preventDefault();
                        console.log('Login request sent');

                        // Successful login
                        navigate('/main');
                    }}>


                        <div className="form-group">
                            <label htmlFor="email">Username</label>
                            <input
                                type="text"
                                id="userLogin"
                                name="usernameInput"
                                placeholder="Enter your username"
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="password">Password</label>
                            <input
                                type='password'
                                id="password"
                                name="password"
                                placeholder="Enter your password"
                            />
                        </div>

                        <button type="submit" className="login-button">
                            Log In
                        </button>
                    </form>
                </div>
            </main>
        </div>
    );
}

export default Login;
