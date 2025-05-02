import { Outlet, NavLink } from 'react-router-dom';
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from '@/components/ui/navigation-menu';

const Layout = () => {
  return (
    <div className="flex flex-col min-h-screen">
      <div className="flex justify-center py-1">
        <NavigationMenu>
          <NavigationMenuList>
            <NavigationMenuItem>
              <NavLink to="/" end>
                {({ isActive }) => (
                  <NavigationMenuLink className={isActive ? 'font-bold' : ''}>
                    공고
                  </NavigationMenuLink>
                )}
              </NavLink>
            </NavigationMenuItem>
            <NavigationMenuItem>
              <NavLink to="/match">
                {({ isActive }) => (
                  <NavigationMenuLink className={isActive ? 'font-bold' : ''}>
                    매칭
                  </NavigationMenuLink>
                )}
              </NavLink>
            </NavigationMenuItem>
          </NavigationMenuList>
        </NavigationMenu>
      </div>
      <div className="flex-1 flex justify-center">
        <Outlet />
      </div>
    </div>
  );
};

export default Layout;
