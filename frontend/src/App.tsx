import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Login } from './Login';
import { ProjectHub } from './Coursepage';
import { Profile } from './Profile';
import { AuthProvider } from './AuthProvider';
import { RequireAuth } from './RequireAuth';
import { ProjectDetail } from './ProjectDetail';
import './App.css';

const ProjectEditor = lazy(() => import('./ProjectEditor').then(module => ({ default: module.ProjectEditor })));
const MyProjects = lazy(() => import('./MyProjects').then(module => ({ default: module.MyProjects })));

function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Suspense fallback={<p role="status">Loading page…</p>}>
                    <Routes>
                        <Route path='/' element={<Login/>}/>
                        <Route element={<RequireAuth/>}>
                            <Route path='/main' element={<ProjectHub/>}/>
                            <Route path='/profile' element={<Profile/>}/>
                            <Route path='/my-projects' element={<MyProjects/>}/>
                            <Route path='/projects/new' element={<ProjectEditor/>}/>
                            <Route path='/projects/:projectId/edit' element={<ProjectEditor/>}/>
                            <Route path='/projects/:projectId' element={<ProjectDetail/>}/>
                        </Route>
                    </Routes>
                </Suspense>
            </BrowserRouter>
        </AuthProvider>
    );
}

export default App;
