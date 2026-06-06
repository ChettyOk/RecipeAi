import { formatAnimatedDecimal, formatAnimatedInt, useAnimatedNumber } from "../lib/useAnimatedNumber";

type Props = {
  value: number | null | undefined;
  duration?: number;
  decimals?: number;
  suffix?: string;
  className?: string;
};

export function AnimatedNumber({ value, duration = 150, decimals = 0, suffix = "", className }: Props) {
  const n = useAnimatedNumber(value, duration);
  const text = decimals > 0 ? formatAnimatedDecimal(n, decimals) : formatAnimatedInt(n);
  return (
    <span className={className}>
      {text}
      {suffix}
    </span>
  );
}
