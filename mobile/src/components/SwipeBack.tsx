import { ReactNode, useMemo } from 'react';
import { PanResponder, View } from 'react-native';
export function shouldSwipeBack(startX: number, dx: number, dy: number) {
  return startX <= 28 && dx > 25 && dx > Math.abs(dy) * 2;
}
export function SwipeBack({ children, canGoBack, goBack }: { children: ReactNode; canGoBack: () => boolean; goBack: () => void }) {
  const responder = useMemo(() => PanResponder.create({
    onMoveShouldSetPanResponder: (_, gesture) => canGoBack() && shouldSwipeBack(gesture.x0, gesture.dx, gesture.dy),
    onPanResponderRelease: (_, gesture) => {
      if (gesture.dx >= 60 && Math.abs(gesture.dy) < gesture.dx / 2 && canGoBack()) goBack();
    },
  }), [canGoBack, goBack]);
  return <View style={{ flex: 1 }} {...responder.panHandlers}>{children}</View>;
}
