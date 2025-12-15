'use client';

import React from 'react';
import { MainLayout } from './MainLayout';
import { PageHeader } from './PageHeader';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

export const LayoutTestSimple: React.FC = () => {
  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Layout Test"
          subtitle="Testing the basic layout components"
        />
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Test Card 1</CardTitle>
              <CardDescription>This is a test card to verify layout</CardDescription>
            </CardHeader>
            <CardContent>
              <p>This card should be properly positioned within the layout grid.</p>
              <Button className="mt-4">Test Button</Button>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Test Card 2</CardTitle>
              <CardDescription>Another test card for verification</CardDescription>
            </CardHeader>
            <CardContent>
              <p>This card should also be properly positioned.</p>
              <Button className="mt-4" variant="outline">Outline Button</Button>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Test Card 3</CardTitle>
              <CardDescription>Final test card</CardDescription>
            </CardHeader>
            <CardContent>
              <p>This completes our basic layout test.</p>
              <Button className="mt-4" variant="secondary">Secondary Button</Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
};
