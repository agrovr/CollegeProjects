#ifndef VPET_SPECIES_DRAGON_H
#define VPET_SPECIES_DRAGON_H

#include "core/Pet.h"

namespace vpet {

class Dragon : public Pet {
public:
    explicit Dragon(const std::string& name);

    std::string species() const override;
    std::array<SpecialAction, 2> specialActions() const override;
    std::vector<PetEvent> events() const override;
};

}  // namespace vpet

#endif
