import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Login } from './Login';
import { ProjectHub } from './Coursepage';

// import { Profile } from './Profile';

function App() {
    return (
        <BrowserRouter>
          <Routes>
            <Route path='/' element={<Login/>}/>
            <Route path='/main' element={<ProjectHub/>}/>
          </Routes>
        </BrowserRouter>

    );
}

export default App;