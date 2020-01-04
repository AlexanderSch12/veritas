#include <exception>
#include <limits>
#include <tuple>
#include <sstream>
#include <iostream>

#include "domain.h"

namespace treeck {

    RealDomain::RealDomain()
        : lo(-std::numeric_limits<FloatT>::infinity())
        , hi(std::numeric_limits<FloatT>::infinity()) {}

    RealDomain::RealDomain(FloatT lo, FloatT hi)
        : lo(lo)
        , hi(hi)
    {
        if (lo >= hi)
        {
            std::stringstream s;
            s << "RealDomain Error: lo >= hi: [" << lo << ", " << hi << ")";
            throw std::invalid_argument(s.str());
        }
    }

    bool
    RealDomain::is_everything() const
    {
        return lo == -std::numeric_limits<FloatT>::infinity()
            && hi == std::numeric_limits<FloatT>::infinity();
    }

    WhereFlag
    RealDomain::where_is(FloatT value) const
    {
        if (hi <= value) // hi is excluded from the domain
            return WhereFlag::RIGHT;
        else if (lo > value) // lo is included in the domain
            return WhereFlag::LEFT;
        return WhereFlag::IN_DOMAIN;
    }

    WhereFlag
    RealDomain::where_is_strict(FloatT value) const
    {
        if (hi <= value)
            return WhereFlag::RIGHT;
        else if (lo >= value) // note <= instead of <
            return WhereFlag::LEFT;
        return WhereFlag::IN_DOMAIN; // does not include lo, hi
    }

    bool
    RealDomain::contains(FloatT value) const
    {
        return where_is(value) == WhereFlag::IN_DOMAIN;
    }

    bool
    RealDomain::contains_strict(FloatT value) const
    {
        return where_is_strict(value) == WhereFlag::IN_DOMAIN;
    }

    bool
    RealDomain::overlaps(const RealDomain& other) const
    {
        return this->lo < other.hi && this->hi > other.lo;
    }

    bool
    RealDomain::covers(const RealDomain& other) const
    {
        return where_is(other.lo) == WhereFlag::IN_DOMAIN
            && where_is(other.hi) == WhereFlag::IN_DOMAIN;
    }

    bool
    RealDomain::covers_strict(const RealDomain& other) const
    {
        return where_is_strict(other.lo) == WhereFlag::IN_DOMAIN
            && where_is_strict(other.hi) == WhereFlag::IN_DOMAIN;
    }

    
    std::tuple<RealDomain, RealDomain>
    RealDomain::split(FloatT value) const
    {
        return std::make_tuple(
                RealDomain(this->lo, value),
                RealDomain(value, this->hi));
    }

    std::ostream&
    operator<<(std::ostream& s, const RealDomain& d)
    {
        return s << "RealDomain(" << d.lo << ", " << d.hi << ')';
    }

} /* namespace treeck */
