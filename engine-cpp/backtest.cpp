// C ABI for a fee-aware, long/flat momentum kernel. No Python calls in the hot loop.
#include <cmath>
#include <cstddef>
#ifdef _WIN32
#define EXPORT extern "C" __declspec(dllexport)
#else
#define EXPORT extern "C"
#endif

EXPORT int momentum_backtest(const double* mid, const double* bid, const double* ask,
    std::size_t n, std::size_t lookback, double qty, double fee_bps, double slip_bps,
    double* equity, double* deltas, double* prices, double* fees) noexcept {
    if (!mid || !bid || !ask || !equity || !deltas || !prices || !fees || !lookback ||
        !std::isfinite(qty) || qty <= 0 || !std::isfinite(fee_bps) || fee_bps < 0 ||
        !std::isfinite(slip_bps) || slip_bps < 0 || slip_bps >= 10000) return 1;
    double cash = 1000000.0, position = 0.0;
    for (std::size_t i = 0; i < n; ++i) {
        if (!std::isfinite(mid[i]) || !std::isfinite(bid[i]) || !std::isfinite(ask[i]) ||
            mid[i] <= 0 || bid[i] <= 0 || ask[i] < bid[i]) return 2;
        const double target = i >= lookback && mid[i] > mid[i-lookback] ? qty : 0.0;
        const double delta = target-position;
        deltas[i] = prices[i] = fees[i] = 0.0;
        if (std::abs(delta) > 1e-9) {
            const double base = delta > 0 ? ask[i] : bid[i];
            const double slip = base * (slip_bps / 10000.0);
            const double price = delta > 0 ? base+slip : base-slip;
            const double amount = std::abs(delta);
            const double fee = amount * price * (fee_bps / 10000.0);
            cash -= delta * price;
            cash -= fee;
            position = target;
            deltas[i] = delta; prices[i] = price; fees[i] = fee;
        }
        equity[i] = cash + position*mid[i];
        if (!std::isfinite(equity[i])) return 3;
    }
    return 0;
}
