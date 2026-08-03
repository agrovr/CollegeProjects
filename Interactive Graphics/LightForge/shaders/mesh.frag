#version 120

uniform int renderMode;
uniform vec3 blueLight;
uniform vec3 redLight;
uniform vec3 baseColor;
uniform float shininess;

varying vec3 eyePosition;
varying vec3 eyeNormal;
varying vec3 vertexColor;

vec3 shade(vec3 normal, vec3 position, bool toon) {
    vec3 viewDirection = normalize(-position);
    vec3 result = baseColor * 0.075;
    vec3 lightPositions[2];
    vec3 lightColors[2];
    lightPositions[0] = blueLight;
    lightPositions[1] = redLight;
    lightColors[0] = vec3(0.12, 0.42, 1.00);
    lightColors[1] = vec3(1.00, 0.16, 0.08);

    for (int index = 0; index < 2; index++) {
        vec3 lightDirection = normalize(lightPositions[index] - position);
        float diffuse = max(dot(normal, lightDirection), 0.0);
        if (toon) {
            diffuse = floor(diffuse * 4.0) / 3.0;
        }
        vec3 halfVector = normalize(lightDirection + viewDirection);
        float specular = pow(max(dot(normal, halfVector), 0.0), shininess);
        result += baseColor * lightColors[index] * diffuse * 0.92;
        if (!toon) {
            result += lightColors[index] * specular * 0.62;
        }
    }
    return result;
}

void main() {
    vec3 normal = normalize(eyeNormal);
    if (renderMode == 1) {
        gl_FragColor = vec4(vertexColor, 1.0);
    } else if (renderMode == 3) {
        gl_FragColor = vec4(normal * 0.5 + 0.5, 1.0);
    } else {
        gl_FragColor = vec4(shade(normal, eyePosition, renderMode == 4), 1.0);
    }
}
