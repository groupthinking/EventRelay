import React from 'react';
import { MainLayout } from "../layout/MainLayout";
import { GeneratorConsole } from "../generator/GeneratorConsole";
import { DashboardProps } from "../../types/project";

export function Dashboard(props: DashboardProps) {
  return (
    <MainLayout>
      <GeneratorConsole />
    </MainLayout>
  );
}

