import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from '@/components/ui/navigation-menu';
import { ModeToggle } from '@/components/mode-toggle';

const Layout = () => {
  const location = useLocation();

  return (
    <div className="flex flex-col min-h-screen">
      <div className="flex justify-between py-1 w-full max-w-3xl mx-auto">
        <div className="flex justify-center w-full ml-15">
          <NavigationMenu className="flex">
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
        <div className="flex-1 align-center justify-end pr-6">
          <ModeToggle />
        </div>
      </div>
      <div className="flex-1 flex justify-center">
        <Outlet />
      </div>
    </div>
  );
};

export default Layout;
