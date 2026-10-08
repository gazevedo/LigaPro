import { useEffect, useRef, useState } from 'react';
import { Text } from 'react-native';
export function ConnectionRetry({ onRetry }: { onRetry: () => void }) {
  const [seconds, setSeconds] = useState(5);
  const retry = useRef(onRetry);
  retry.current = onRetry;
  useEffect(() => {
    let remaining = 5;
    const timer = setInterval(() => {
      remaining--;
      setSeconds(remaining);
      if (remaining === 0) {
        clearInterval(timer);
        retry.current();
      }
    }, 1000);
    return () => clearInterval(timer);
  }, []);
  return <Text accessibilityLiveRegion="polite">{seconds > 0 ? `Nova tentativa em ${seconds}s…` : 'Reconectando…'}</Text>;
}
