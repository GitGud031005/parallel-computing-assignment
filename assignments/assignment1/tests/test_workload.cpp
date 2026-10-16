#include "test_support.hpp"
#include "pc/common/workload.hpp"
#include "pc/common/cli.hpp"
#include <limits>

bool oracle(std::uint32_t n) {
    if (n < 2) return false;
    for (std::uint32_t d = 2; d <= n / d; ++d) if (n % d == 0) return false;
    return true;
}
int main() {
    return test::main([] {
        test::run("naive prime vs independent sqrt oracle [0,10009]", [] {
            for (std::uint32_t n = 0; n <= 10009; ++n)
                test::require(pc::is_prime(n) == oracle(n), "primality mismatch at " + std::to_string(n));
        });
        test::run("fixed-total quotient/remainder including K<P", [] {
            for (std::size_t p = 1; p <= 19; ++p)
                for (std::uint64_t total = 0; total <= 101; ++total) {
                    std::uint64_t sum = 0;
                    for (std::size_t id = 0; id < p; ++id) sum += pc::share(total, p, id);
                    test::require(sum == total, "partition lost operations");
                }
        });
        test::run("overflow validation", [] {
            auto max = std::numeric_limits<std::uint64_t>::max();
            test::require(pc::checked_mul(max, 1) == max && pc::checked_add(max, 0) == max, "valid boundary");
            bool add = false, mul = false;
            try { (void)pc::checked_add(max, 1); } catch (const std::invalid_argument&) { add = true; }
            try { (void)pc::checked_mul(max, 2); } catch (const std::invalid_argument&) { mul = true; }
            test::require(add && mul, "overflow not rejected");
        });
    });
}
