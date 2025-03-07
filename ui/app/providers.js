import { ScrollProvider } from "@/contexts/ScrollContext";

const Providers = ({ children }) => {
  return <ScrollProvider>{children}</ScrollProvider>;
};

export default Providers;
