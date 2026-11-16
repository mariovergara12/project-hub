import { useNavigate } from 'react-router-dom'; 


export function Login() {
const navigate = useNavigate();


    return (
        <div className="pageTitle">
            <header>
                <h1>Project Hub</h1>
            </header>

            <main className="basic-container">
                <div className="login-card">
                    <form onSubmit={async(event) => {
                        event.preventDefault();
                        const whichButton = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement;
                        const formData = new FormData(event.currentTarget);
                        const email = formData.get('emailInput');
                        const password = formData.get('passwordInput');

                        console.log(email);
                        console.log(password);

                        console.log(whichButton.value);
                        if (whichButton.value === 'login') {
                            console.log("ATTEMPTING LOGIN....")
                        } 
                        else if (whichButton.value === 'signup') {
                            console.log("ATTEMPTING SIGNING UP....")
                        }

                        // Successful login
                        navigate('/main');
                    }}>


                        <div className="form-group">
                            <label htmlFor="email">Email</label>
                            <input
                                type="text"
                                id="userLogin"
                                name="emailInput"
                                placeholder="Enter your email"
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="password">Password</label>
                            <input
                                type='password'
                                id="password"
                                name="passwordInput"
                                placeholder="Enter your password"
                            />
                        </div>

                        <button type="submit" className="login-button" value="login">
                            Log In
                        </button>

                        <button type="submit" className="signup-button" value="signup">
                            Sign Up
                        </button>
                    </form>
                </div>
            </main>
        </div>
    );
}

export default Login;
