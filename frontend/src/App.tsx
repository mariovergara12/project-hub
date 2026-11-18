import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Login } from './pages/Login';
import { ProjectHub } from './pages/Coursepage';
import { Profile } from './pages/Profile';
import { UserProject } from './pages/CreateProject';
import { Projects } from './pages/Projects';

import { AuthProvider } from './AuthProvider';
import { RequireAuth } from './pages/RequireAuth';
import './App.css';
import EditProfile from './pages/EditProfile';

function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Routes>
                    <Route path='/' element={<Login/>}/>
                    <Route element={<RequireAuth/>}>
                        <Route path='/main' element={<ProjectHub/>}/>
                        <Route path='/profile' element={<Profile/>}/>
                        <Route path='/createproject' element={<UserProject/>}/>
                        <Route path='/editprofile' element={<EditProfile/>}/>
                        <Route path='projects' element={<Projects/>}/>
                    </Route>
                </Routes>
            </BrowserRouter>
        </AuthProvider>
    );
}

export default App;
