#ifndef VPET_SPECIES_UNICORN_H
#define VPET_SPECIES_UNICORN_H

#include "core/Pet.h"

namespace vpet {

class Unicorn : public Pet {
public:
    explicit Unicorn(const std::string& name);

    std::string species() const override;
    std::array<SpecialAction, 2> specialActions() const override;
    std::vector<PetEvent> events() const override;
};

}  // namespace vpet

#endif
