#ifndef MYSTIC_CAT_H
#define MYSTIC_CAT_H

#include "Pet.h"

class MysticCat : public Pet {
public:
    explicit MysticCat(const std::string& name);

    std::string species() const override;
    std::array<std::string, 2> specialActionNames() const override;
    std::string performSpecialAction(std::size_t index) override;
};

#endif
