import { Outlet, Link } from 'react-router-dom';

const Layout = () => {
  return (
    <>
      <nav>
        <ul>
          <li>
            <Link to="/">JobList</Link>
          </li>
          <li>
            <Link to="/match">JobMatcher</Link>
          </li>
        </ul>
      </nav>

      <Outlet />
    </>
  );
};

export default Layout;
