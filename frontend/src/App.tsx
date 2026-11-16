import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Login } from './Login';
import { ProjectHub } from './Coursepage';
import { Profile } from './Profile';
import { AuthProvider } from './AuthProvider';
import { RequireAuth } from './RequireAuth';
import { ProjectDetail } from './ProjectDetail';
import './App.css';

function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Routes>
                    <Route path='/' element={<Login/>}/>
                    <Route element={<RequireAuth/>}>
                        <Route path='/main' element={<ProjectHub/>}/>
                        <Route path='/profile' element={<Profile/>}/>
                        <Route path='/projects/:projectId' element={<ProjectDetail/>}/>
                    </Route>
                </Routes>
            </BrowserRouter>
        </AuthProvider>
    );
}

export default App;
