import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, Users, Clock, DollarSign, Lightbulb, Zap, Award } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// Mock Data for "VidiQ-style" Growth Graph
const data = [
    { name: 'Mon', views: 4000, subs: 240 },
    { name: 'Tue', views: 3000, subs: 139 },
    { name: 'Wed', views: 2000, subs: 980 },
    { name: 'Thu', views: 2780, subs: 390 },
    { name: 'Fri', views: 1890, subs: 480 },
    { name: 'Sat', views: 2390, subs: 380 },
    { name: 'Sun', views: 3490, subs: 430 },
];

const outliers = [
    { title: "How to Build AI Agents in 2025", score: 98, views: "125K" },
    { title: "Python vs Rust for AI", score: 92, views: "89K" },
    { title: "The End of Coding?", score: 87, views: "210K" }
];

export function AnalyticsDashboard() {
    return (
        <div className="p-6 space-y-8 max-w-7xl mx-auto">

            {/* Header Section */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Channel Analytics</h1>
                    <p className="text-muted-foreground mt-1">
                        Real-time insights and growth opportunities (VidiQ Style)
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline"><Clock className="mr-2 h-4 w-4" /> Last 7 Days</Button>
                    <Button className="bg-[#0092b8] hover:bg-[#007a99] text-white">
                        <Zap className="mr-2 h-4 w-4" /> Boost Channel
                    </Button>
                </div>
            </div>

            {/* Top Stats Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Views</CardTitle>
                        <TrendingUp className="h-4 w-4 text-[#0092b8]" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">142,384</div>
                        <p className="text-xs text-muted-foreground">+20.1% from last month</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Subscribers</CardTitle>
                        <Users className="h-4 w-4 text-[#0092b8]" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">+2,450</div>
                        <p className="text-xs text-muted-foreground">+180.1% from last month</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Watch Time (hrs)</CardTitle>
                        <Clock className="h-4 w-4 text-[#0092b8]" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">12,234</div>
                        <p className="text-xs text-muted-foreground">+19% from last month</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Est. Revenue</CardTitle>
                        <DollarSign className="h-4 w-4 text-green-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">$4,329.00</div>
                        <p className="text-xs text-muted-foreground">+7% from last month</p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-7">

                {/* Main Growth Graph */}
                <Card className="col-span-4">
                    <CardHeader>
                        <CardTitle>Growth Velocity</CardTitle>
                        <CardDescription>Views vs Subscribers over time</CardDescription>
                    </CardHeader>
                    <CardContent className="pl-2">
                        <div className="h-[300px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={data}>
                                    <defs>
                                        <linearGradient id="colorViews" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#0092b8" stopOpacity={0.8} />
                                            <stop offset="95%" stopColor="#0092b8" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <XAxis dataKey="name" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                                    <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `${value}`} />
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.1)" />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', color: '#fff' }}
                                    />
                                    <Area type="monotone" dataKey="views" stroke="#0092b8" fillOpacity={1} fill="url(#colorViews)" />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>

                {/* Daily Ideas / Outliers */}
                <Card className="col-span-3">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Lightbulb className="h-5 w-5 text-yellow-500" />
                            Daily Ideas & Outliers
                        </CardTitle>
                        <CardDescription>High potential topics based on your niche</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {outliers.map((item, i) => (
                                <div key={i} className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors cursor-pointer">
                                    <div className="space-y-1">
                                        <p className="font-medium leading-none">{item.title}</p>
                                        <p className="text-sm text-muted-foreground">{item.views} potential views</p>
                                    </div>
                                    <div className="flex items-center gap-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 px-2 py-1 rounded text-xs font-bold">
                                        <Award className="h-3 w-3" />
                                        {item.score}/100
                                    </div>
                                </div>
                            ))}
                            <Button variant="ghost" className="w-full text-[#0092b8]">View All 15 Ideas</Button>
                        </div>
                    </CardContent>
                </Card>

            </div>

            {/* Achievements / Gamification */}
            <Card>
                <CardHeader>
                    <CardTitle>Next Achievements</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex gap-4 overflow-x-auto pb-2">
                        {[1, 2, 3, 4].map((_, i) => (
                            <div key={i} className="min-w-[200px] p-4 border rounded-lg bg-gradient-to-br from-muted/50 to-muted/10">
                                <div className="h-8 w-8 rounded-full bg-[#0092b8]/20 flex items-center justify-center mb-3">
                                    <Zap className="h-4 w-4 text-[#0092b8]" />
                                </div>
                                <h4 className="font-semibold mb-1">10k Subscribers</h4>
                                <div className="w-full bg-secondary h-2 rounded-full mt-2">
                                    <div className="bg-[#0092b8] h-2 rounded-full" style={{ width: '75%' }}></div>
                                </div>
                                <p className="text-xs text-muted-foreground mt-2">7,500 / 10,000</p>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

        </div>
    );
}
