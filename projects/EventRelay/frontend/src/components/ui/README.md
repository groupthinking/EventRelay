# Progress Components

A comprehensive collection of animated progress tracking components for React applications. These components provide various ways to visualize progress, status, and loading states with smooth animations and customizable styling.

## 🚀 Features

- **Smooth Animations**: CSS transitions and animations for all components
- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **TypeScript Support**: Full type safety with comprehensive interfaces
- **Customizable**: Multiple variants, sizes, and color schemes
- **Accessible**: Proper ARIA labels and semantic HTML
- **Performance Optimized**: Efficient rendering with React hooks

## 📦 Components Overview

### 1. Progress Bar
- Linear progress visualization
- Step-based progress tracking
- ETA and speed indicators
- Multiple status colors

### 2. Progress Steps
- Step-by-step progress visualization
- Interactive step indicators
- Progress line connections
- Step timing information

### 3. Progress Circle
- Circular progress indicators
- Multiple size variants
- Status-based styling
- Custom center content

### 4. Progress Timeline
- Time-based event tracking
- Chronological event display
- Event metadata support
- Auto-advance capabilities

### 5. Progress Spinner
- Multiple loading animations
- Different spinner variants
- Progress integration
- Loading overlays

### 6. Progress Status
- Status badges and indicators
- Multiple status types
- Status grouping
- Status timelines

## 🎯 Usage Examples

### Basic Progress Bar

```tsx
import { ProgressBar } from './components/ui';

function MyComponent() {
  return (
    <ProgressBar
      currentStep={2}
      totalSteps={5}
      status="processing"
      animated={true}
    />
  );
}
```

### Enhanced Progress Steps

```tsx
import { EnhancedProgressSteps } from './components/ui';

function MyComponent() {
  const steps = [
    { id: '1', label: 'Upload', description: 'Upload file', status: 'completed' },
    { id: '2', label: 'Process', description: 'Process data', status: 'active' },
    { id: '3', label: 'Complete', description: 'Finish task', status: 'pending' }
  ];

  return (
    <EnhancedProgressSteps
      steps={steps}
      currentStepIndex={1}
      showProgressBar={true}
      showStepTiming={true}
    />
  );
}
```

### Progress Circle with Status

```tsx
import { ProgressCircle } from './components/ui';

function MyComponent() {
  return (
    <ProgressCircle
      progress={75}
      status="processing"
      size={120}
      showPercentage={true}
      animated={true}
    />
  );
}
```

### Progress Timeline

```tsx
import { ProgressTimeline } from './components/ui';

function MyComponent() {
  const events = [
    {
      id: '1',
      title: 'Task Started',
      description: 'Beginning process',
      timestamp: new Date(),
      status: 'completed'
    }
  ];

  return (
    <ProgressTimeline
      events={events}
      currentEventIndex={0}
      showTimestamps={true}
      variant="detailed"
    />
  );
}
```

### Loading Spinner

```tsx
import { ProgressSpinner } from './components/ui';

function MyComponent() {
  return (
    <ProgressSpinner
      variant="dots"
      size="lg"
      color="primary"
      text="Loading..."
      showText={true}
    />
  );
}
```

### Status Indicators

```tsx
import { ProgressStatus, StatusGroup } from './components/ui';

function MyComponent() {
  const statuses = [
    { id: '1', status: 'completed', text: 'Done' },
    { id: '2', status: 'processing', text: 'Working' }
  ];

  return (
    <div>
      <ProgressStatus status="completed" text="Task Complete" />
      <StatusGroup statuses={statuses} layout="horizontal" />
    </div>
  );
}
```

## 🔧 Component Props

### ProgressBar

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `currentStep` | `number` | `0` | Current step number |
| `totalSteps` | `number` | `1` | Total number of steps |
| `status` | `string` | `'pending'` | Current status |
| `animated` | `boolean` | `true` | Enable animations |
| `showSteps` | `boolean` | `false` | Show step indicators |
| `stepLabels` | `string[]` | `[]` | Labels for each step |
| `className` | `string` | `''` | Additional CSS classes |

### ProgressSteps

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `steps` | `ProgressStep[]` | `[]` | Array of step objects |
| `currentStepIndex` | `number` | `0` | Current step index |
| `showStepNumbers` | `boolean` | `true` | Show step numbers |
| `showStepDescriptions` | `boolean` | `true` | Show step descriptions |
| `animated` | `boolean` | `true` | Enable animations |
| `clickable` | `boolean` | `false` | Make steps clickable |
| `onStepClick` | `function` | `undefined` | Step click handler |

### ProgressCircle

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `progress` | `number` | `0` | Progress percentage (0-100) |
| `size` | `number` | `120` | Circle size in pixels |
| `strokeWidth` | `number` | `8` | Stroke width |
| `status` | `string` | `'pending'` | Current status |
| `animated` | `boolean` | `true` | Enable animations |
| `showPercentage` | `boolean` | `true` | Show percentage |
| `children` | `ReactNode` | `undefined` | Custom center content |

### ProgressTimeline

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `events` | `TimelineEvent[]` | `[]` | Array of timeline events |
| `currentEventIndex` | `number` | `0` | Current event index |
| `showTimestamps` | `boolean` | `true` | Show event timestamps |
| `showDurations` | `boolean` | `false` | Show event durations |
| `variant` | `string` | `'default'` | Display variant |
| `animated` | `boolean` | `true` | Enable animations |
| `clickable` | `boolean` | `false` | Make events clickable |

### ProgressSpinner

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | `string` | `'default'` | Spinner animation type |
| `size` | `string` | `'md'` | Spinner size |
| `color` | `string` | `'primary'` | Spinner color |
| `text` | `string` | `''` | Loading text |
| `showText` | `boolean` | `false` | Show loading text |
| `animated` | `boolean` | `true` | Enable animations |

### ProgressStatus

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `status` | `StatusType` | `'pending'` | Status type |
| `text` | `string` | `''` | Status text |
| `showIcon` | `boolean` | `true` | Show status icon |
| `size` | `string` | `'md'` | Status size |
| `variant` | `string` | `'default'` | Display variant |
| `showBadge` | `boolean` | `true` | Show as badge |

## 🎨 Styling and Customization

### CSS Classes

All components use Tailwind CSS classes and can be customized by:

1. **Passing className prop**: Add custom CSS classes
2. **Using Tailwind config**: Modify color schemes and spacing
3. **CSS custom properties**: Override default values

### Color Schemes

Components support multiple status-based color schemes:

- `pending`: Gray
- `active/processing`: Blue
- `completed/success`: Green
- `failed/error`: Red
- `warning`: Yellow
- `info`: Blue (lighter)

### Size Variants

Most components support multiple sizes:

- `sm`: Small (compact)
- `md`: Medium (default)
- `lg`: Large
- `xl`: Extra large

## ♿ Accessibility

All components include:

- Proper ARIA labels and roles
- Keyboard navigation support
- Screen reader compatibility
- High contrast color schemes
- Focus indicators

## 🚀 Performance

Components are optimized for:

- Minimal re-renders
- Efficient DOM updates
- Smooth animations
- Memory management
- Bundle size optimization

## 🔄 State Management

Components support various state management patterns:

- **Local State**: Use React useState for simple state
- **Context**: Share state across components
- **Redux/Zustand**: Integrate with global state
- **Server State**: Real-time progress updates

## 📱 Responsive Design

All components are:

- Mobile-first designed
- Touch-friendly
- Responsive breakpoints
- Adaptive layouts
- Flexible sizing

## 🧪 Testing

Components include:

- TypeScript interfaces
- Prop validation
- Error boundaries
- Test utilities
- Storybook stories

## 📚 Additional Resources

- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [React Documentation](https://reactjs.org/)
- [TypeScript Handbook](https://www.typescriptlang.org/)
- [Accessibility Guidelines](https://www.w3.org/WAI/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
