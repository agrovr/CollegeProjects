#ifndef DRAGON_H
#define DRAGON_H

#include "Pet.h"

class Dragon : public Pet {
public:
    explicit Dragon(const std::string& name);

    std::string species() const override;
    std::array<std::string, 2> specialActionNames() const override;
    std::string performSpecialAction(std::size_t index) override;
};

#endif
