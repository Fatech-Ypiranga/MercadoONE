import { ColorVisionSelect } from "@/components/color-vision-select";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <div className="fixed top-4 right-4 z-40">
        <ColorVisionSelect />
      </div>
      {children}
    </>
  );
}
