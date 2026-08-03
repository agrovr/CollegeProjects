#version 120

varying vec4 particleColor;

void main()
{
    vec2 centered = gl_PointCoord * 2.0 - 1.0;
    float radiusSquared = dot(centered, centered);

    if (radiusSquared > 1.0)
        discard;

    float softEdge = 1.0 - smoothstep(0.20, 1.0, radiusSquared);
    float brightCore = 1.0 - smoothstep(0.0, 0.35, radiusSquared);
    float alpha = particleColor.a * softEdge;
    vec3 glowColor = particleColor.rgb * (0.80 + brightCore * 0.85);

    gl_FragColor = vec4(glowColor, alpha);
}
