
import React from 'react';

interface SectionProps {
  title: string;
  titleColor?: string;
  children: React.ReactNode;
  className?: string;
}

const Section: React.FC<SectionProps> = ({ title, children, titleColor = "text-sky-700", className = "" }) => {
  return (
    <section className={`mb-12 ${className}`}>
      <h2 className={`text-3xl font-bold mb-6 pb-2 border-b-2 border-sky-200 ${titleColor}`}>
        {title}
      </h2>
      {children}
    </section>
  );
};

export default Section;
