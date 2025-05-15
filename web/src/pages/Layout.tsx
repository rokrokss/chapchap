import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from '@/components/ui/navigation-menu';
import { ModeToggle } from '@/components/mode-toggle';
import useResumeStore from '@/store/useResumeStore';
import pray from '@/assets/pray.svg';

const Layout = () => {
  const location = useLocation();
  const { pdfMode } = useResumeStore();

  return (
    <div className="flex flex-col min-h-screen">
      <div className="flex justify-between py-1 w-full max-w-3xl mx-auto">
        <Link to="/">
          <div className="flex items-center justify-start ml-4 pl-3 w-16 cursor-pointer">
            <img src={pray} alt="찹찹" className="h-6 mt-1.5 pl-1" />
          </div>
        </Link>
        <div className="flex justify-center w-full mr-2">
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
                    location.pathname === '/match' || location.pathname === '/match-text'
                      ? 'font-bold text-accent-foreground bg-accent/50 bg-accent'
                      : ''
                  }
                  asChild
                >
                  <Link to={pdfMode ? '/match' : '/match-text'}>취업AI</Link>
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
