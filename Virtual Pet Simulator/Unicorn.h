#ifndef UNICORN_H
#define UNICORN_H

#include "Pet.h"

class Unicorn : public Pet {
public:
    explicit Unicorn(const std::string& name);

    std::string species() const override;
    std::array<std::string, 2> specialActionNames() const override;
    std::string performSpecialAction(std::size_t index) override;
};

#endif
