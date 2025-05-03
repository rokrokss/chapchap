import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from '@/components/ui/navigation-menu';

const Layout = () => {
  const location = useLocation();

  return (
    <div className="flex flex-col min-h-screen">
      <div className="flex justify-center py-1">
        <NavigationMenu>
          <NavigationMenuList>
            <NavigationMenuItem>
              <NavigationMenuLink
                className={
                  location.pathname === '/'
                    ? 'font-bold text-accent-foreground bg-accent/50 bg-accent'
                    : ''
                }
                asChild
              >
                <Link to="/">공고</Link>
              </NavigationMenuLink>
            </NavigationMenuItem>
            <NavigationMenuItem>
              <NavigationMenuLink
                className={
                  location.pathname === '/match'
                    ? 'font-bold text-accent-foreground bg-accent/50 bg-accent'
                    : ''
                }
                asChild
              >
                <Link to="/match">매칭</Link>
              </NavigationMenuLink>
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
