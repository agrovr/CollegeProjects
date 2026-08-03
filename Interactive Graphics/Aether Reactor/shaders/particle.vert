#version 120

uniform float pointScale;
uniform float particleSize;

varying vec4 particleColor;

void main()
{
    vec4 eyePosition = gl_ModelViewMatrix * gl_Vertex;
    float distanceFromCamera = max(1.0, -eyePosition.z);
    gl_Position = gl_ProjectionMatrix * eyePosition;
    gl_PointSize = clamp(particleSize * pointScale / distanceFromCamera,
                         2.0, 72.0);
    particleColor = gl_Color;
}
