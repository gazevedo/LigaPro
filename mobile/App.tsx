import { AppNavigator } from './src/navigation/AppNavigator';
import { useVersionMonitor } from './src/components/useVersionMonitor';
export default function App() { useVersionMonitor(); return <AppNavigator />; }
