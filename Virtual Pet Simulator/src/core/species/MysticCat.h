#ifndef VPET_SPECIES_MYSTICCAT_H
#define VPET_SPECIES_MYSTICCAT_H

#include "core/Pet.h"

namespace vpet {

class MysticCat : public Pet {
public:
    explicit MysticCat(const std::string& name);

    std::string species() const override;
    std::array<SpecialAction, 2> specialActions() const override;
    std::vector<PetEvent> events() const override;
};

}  // namespace vpet

#endif
